package com.demo;

import com.demo.BankAccount;
import java.lang.reflect.Field;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class BankAccount_deposit_Dbl_Test_Normal_4 {


    @Test
    public void testDepositWithValidAmount() throws Exception {
        // Use valid typical input 1.0 to exercise the normal path
        BankAccount account = new BankAccount("Alice", 100.0);

        account.deposit(1.0);

        // Verify side effect: balance should have increased by 1.0
        Field balanceField = BankAccount.class.getDeclaredField("balance");
        balanceField.setAccessible(true);
        double newBalance = balanceField.getDouble(account);

        Assertions.assertEquals(101.0, newBalance, 0.0001);
    }

}
