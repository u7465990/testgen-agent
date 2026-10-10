package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

public class BankAccount_withdraw_Dbl_Test_Normal_6 {


    private BankAccount account;

    @Before
    public void setUp() {
        account = new BankAccount("Alice", 10.0);
    }

    @Test
    public void testWithdrawWithRepresentativeValidInputs() {
        // Withdraw 1.0 from a balance of 10.0
        account.withdraw(1.0);
        Assert.assertEquals(9.0, getBalance(account), 0.0);

        // Withdraw another valid amount to confirm repeated withdrawals work
        account.withdraw(4.0);
        Assert.assertEquals(5.0, getBalance(account), 0.0);
    }

    private double getBalance(BankAccount acc) {
        try {
            java.lang.reflect.Field field = BankAccount.class.getDeclaredField("balance");
            field.setAccessible(true);
            return field.getDouble(acc);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

}
