package com.demo;

import com.demo.BankAccount;
import org.junit.Test;
import static org.junit.Assert.*;

public class BankAccount_getOwner_Test_Path_3 {


    @Test
    public void testGetOwnerReturnsOwner() {
        BankAccount account = new BankAccount("Alice", 100.0);
        assertEquals("Alice", account.getOwner());
    }

}
