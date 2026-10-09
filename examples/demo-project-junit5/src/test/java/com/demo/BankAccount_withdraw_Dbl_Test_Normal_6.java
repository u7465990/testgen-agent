package com.demo;

import com.demo.BankAccount;
import java.lang.reflect.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class BankAccount_withdraw_Dbl_Test_Normal_6 {

    private double getBalance(BankAccount account) throws Exception {
        Field field = BankAccount.class.getDeclaredField("balance");
        field.setAccessible(true);
        return (Double) field.get(account);
    }

    @Test
    public void testWithdrawWithValidAmount() throws Exception {
        BankAccount account = new BankAccount("Alice", 100.0);
        assertEquals(100.0, getBalance(account), 1e-9);

        account.withdraw(1.0);

        assertEquals(99.0, getBalance(account), 1e-9);
    }

    @Test
    public void testWithdrawExactBalance() throws Exception {
        BankAccount account = new BankAccount("Bob", 50.0);

        account.withdraw(50.0);

        assertEquals(0.0, getBalance(account), 1e-9);
    }

    @Test
    public void testWithdrawFractionalAmount() throws Exception {
        BankAccount account = new BankAccount("Carol", 10.0);

        account.withdraw(0.5);

        assertEquals(9.5, getBalance(account), 1e-9);
    }

}